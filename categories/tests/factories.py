"""factory-boy factories for Category."""

import factory
from factory.django import DjangoModelFactory

from categories.models import Category, CategoryHide
from transactions.tests.factories import UserFactory


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    user = factory.SubFactory(UserFactory)
    type = "expense"
    slug = factory.Sequence(lambda n: f"category-{n}")
    name = factory.Faker("word")
    emoji = "📁"


class CategoryHideFactory(DjangoModelFactory):
    class Meta:
        model = CategoryHide

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
