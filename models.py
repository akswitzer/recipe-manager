"""Database models for the recipe manager."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Recipe(db.Model):
    """A recipe with ingredients and instructions."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Dinner')
    servings = db.Column(db.Integer, default=4)
    prep_time = db.Column(db.Integer)  # minutes
    cook_time = db.Column(db.Integer)  # minutes
    instructions = db.Column(db.Text)

    # Macros per serving
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)  # grams
    carbs = db.Column(db.Float)    # grams
    fat = db.Column(db.Float)      # grams

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ingredients = db.relationship('Ingredient', backref='recipe', lazy=True, cascade='all, delete-orphan')

    @property
    def total_time(self):
        """Total prep + cook time."""
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        return prep + cook

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'servings': self.servings,
            'prep_time': self.prep_time,
            'cook_time': self.cook_time,
            'instructions': self.instructions,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fat': self.fat,
            'ingredients': [i.to_dict() for i in self.ingredients]
        }


class Ingredient(db.Model):
    """An ingredient for a recipe."""

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float)
    unit = db.Column(db.String(30))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'unit': self.unit
        }

    def scaled(self, multiplier):
        """Return ingredient with scaled amount."""
        return {
            'name': self.name,
            'amount': round(self.amount * multiplier, 2) if self.amount else None,
            'unit': self.unit
        }


# Category options
CATEGORIES = ['Breakfast', 'Lunch', 'Dinner', 'Dessert', 'Snack', 'Drink', 'Side']

# Common units for the dropdown
UNITS = ['', 'cup', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'L', 'piece', 'slice', 'clove', 'can', 'bunch']
