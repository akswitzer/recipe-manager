"""Main Flask application for the Recipe Manager."""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Recipe, Ingredient, CATEGORIES, UNITS

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables on first run
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """Home page - list all recipes with search and filter."""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')

    query = Recipe.query

    if search:
        # Search in title and ingredients
        query = query.outerjoin(Ingredient).filter(
            db.or_(
                Recipe.title.ilike(f'%{search}%'),
                Recipe.description.ilike(f'%{search}%'),
                Ingredient.name.ilike(f'%{search}%')
            )
        ).distinct()

    if category:
        query = query.filter(Recipe.category == category)

    recipes = query.order_by(Recipe.updated_at.desc()).all()

    return render_template('index.html',
                         recipes=recipes,
                         categories=CATEGORIES,
                         search=search,
                         selected_category=category)


@app.route('/recipe/<int:id>')
def view_recipe(id):
    """View a single recipe with optional serving adjustment."""
    recipe = Recipe.query.get_or_404(id)
    servings = request.args.get('servings', recipe.servings, type=int)
    multiplier = servings / recipe.servings if recipe.servings else 1

    scaled_ingredients = [ing.scaled(multiplier) for ing in recipe.ingredients]

    return render_template('recipe.html',
                         recipe=recipe,
                         servings=servings,
                         scaled_ingredients=scaled_ingredients)


@app.route('/recipe/new', methods=['GET', 'POST'])
def new_recipe():
    """Create a new recipe."""
    if request.method == 'POST':
        recipe = Recipe(
            title=request.form['title'],
            description=request.form.get('description', ''),
            category=request.form.get('category', 'Dinner'),
            servings=int(request.form.get('servings', 4)),
            prep_time=int(request.form['prep_time']) if request.form.get('prep_time') else None,
            cook_time=int(request.form['cook_time']) if request.form.get('cook_time') else None,
            instructions=request.form.get('instructions', '')
        )

        # Add ingredients
        names = request.form.getlist('ingredient_name[]')
        amounts = request.form.getlist('ingredient_amount[]')
        units = request.form.getlist('ingredient_unit[]')

        for name, amount, unit in zip(names, amounts, units):
            if name.strip():
                ingredient = Ingredient(
                    name=name.strip(),
                    amount=float(amount) if amount else None,
                    unit=unit
                )
                recipe.ingredients.append(ingredient)

        db.session.add(recipe)
        db.session.commit()
        flash(f'Recipe "{recipe.title}" created!', 'success')
        return redirect(url_for('view_recipe', id=recipe.id))

    return render_template('edit.html',
                         recipe=None,
                         categories=CATEGORIES,
                         units=UNITS)


@app.route('/recipe/<int:id>/edit', methods=['GET', 'POST'])
def edit_recipe(id):
    """Edit an existing recipe."""
    recipe = Recipe.query.get_or_404(id)

    if request.method == 'POST':
        recipe.title = request.form['title']
        recipe.description = request.form.get('description', '')
        recipe.category = request.form.get('category', 'Dinner')
        recipe.servings = int(request.form.get('servings', 4))
        recipe.prep_time = int(request.form['prep_time']) if request.form.get('prep_time') else None
        recipe.cook_time = int(request.form['cook_time']) if request.form.get('cook_time') else None
        recipe.instructions = request.form.get('instructions', '')

        # Clear existing ingredients and re-add
        recipe.ingredients.clear()

        names = request.form.getlist('ingredient_name[]')
        amounts = request.form.getlist('ingredient_amount[]')
        units = request.form.getlist('ingredient_unit[]')

        for name, amount, unit in zip(names, amounts, units):
            if name.strip():
                ingredient = Ingredient(
                    name=name.strip(),
                    amount=float(amount) if amount else None,
                    unit=unit
                )
                recipe.ingredients.append(ingredient)

        db.session.commit()
        flash(f'Recipe "{recipe.title}" updated!', 'success')
        return redirect(url_for('view_recipe', id=recipe.id))

    return render_template('edit.html',
                         recipe=recipe,
                         categories=CATEGORIES,
                         units=UNITS)


@app.route('/recipe/<int:id>/delete', methods=['POST'])
def delete_recipe(id):
    """Delete a recipe."""
    recipe = Recipe.query.get_or_404(id)
    title = recipe.title
    db.session.delete(recipe)
    db.session.commit()
    flash(f'Recipe "{title}" deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/shopping-list', methods=['GET', 'POST'])
def shopping_list():
    """Generate a shopping list from selected recipes."""
    recipes = Recipe.query.order_by(Recipe.title).all()
    shopping_items = []
    selected_ids = []

    if request.method == 'POST':
        selected_ids = [int(id) for id in request.form.getlist('recipes')]
        servings_map = {}

        for recipe_id in selected_ids:
            servings_map[recipe_id] = int(request.form.get(f'servings_{recipe_id}', 4))

        # Aggregate ingredients
        ingredient_totals = {}

        for recipe_id in selected_ids:
            recipe = Recipe.query.get(recipe_id)
            if recipe:
                multiplier = servings_map[recipe_id] / recipe.servings if recipe.servings else 1

                for ing in recipe.ingredients:
                    key = (ing.name.lower(), ing.unit or '')
                    scaled_amount = (ing.amount or 0) * multiplier

                    if key in ingredient_totals:
                        ingredient_totals[key]['amount'] += scaled_amount
                        ingredient_totals[key]['recipes'].append(recipe.title)
                    else:
                        ingredient_totals[key] = {
                            'name': ing.name,
                            'amount': scaled_amount,
                            'unit': ing.unit or '',
                            'recipes': [recipe.title]
                        }

        # Sort by ingredient name
        shopping_items = sorted(ingredient_totals.values(), key=lambda x: x['name'].lower())

    return render_template('shopping.html',
                         recipes=recipes,
                         shopping_items=shopping_items,
                         selected_ids=selected_ids)


@app.route('/api/recipes')
def api_recipes():
    """JSON API endpoint for recipes."""
    recipes = Recipe.query.all()
    return jsonify([r.to_dict() for r in recipes])


if __name__ == '__main__':
    app.run(debug=True, port=5000)
