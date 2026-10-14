# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Product API Service Test Suite

Test cases can be run with:
    nosetests
    coverage report -m
"""

import os
import logging
import unittest
from service import app
from service.models import db, Product
from service.common import status
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/products"


######################################################################
#  P R O D U C T   A P I   S E R V I C E   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(unittest.TestCase):
    """Test Cases for Product API Service"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################
    def _create_products(self, count):
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test product",
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["message"], "Healthy")

    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_get_product(self):
        """It should Get a single Product"""
        # get the id of a product
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)
        self.assertEqual(data["available"], test_product.available)
        self.assertEqual(data["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """It should not Get a Product thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    def test_update_product(self):
        """It should Update an existing Product"""
        # create a product to update
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update the product
        new_product = response.get_json()
        new_product["description"] = "testing"
        response = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["description"], "testing")

    def test_update_product_not_found(self):
        """It should not Update a Product that is not found"""
        test_product = ProductFactory()
        response = self.client.put(
            f"{BASE_URL}/0", json=test_product.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

        # make sure it is gone
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """It should not Delete a Product that is not found"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_product_list(self):
        """It should Get a list of Products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_get_product_by_name(self):
        """It should Get a Product by name"""
        products = self._create_products(5)
        name = products[0].name
        count = len([p for p in products if p.name == name])
        response = self.client.get(f"{BASE_URL}?name={name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["name"], name)

    def test_get_product_by_category(self):
        """It should Get a Product by category"""
        products = self._create_products(10)
        category = products[0].category.name
        count = len([p for p in products if p.category.name == category])
        response = self.client.get(f"{BASE_URL}?category={category}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["category"], category)

    def test_get_product_by_availability(self):
        """It should Get a Product by availability"""
        products = self._create_products(10)
        available = products[0].available
        count = len([p for p in products if p.available == available])
        response = self.client.get(f"{BASE_URL}?available={str(available).lower()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["available"], available)

    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""
        response = self.client.put(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_product_no_content_type(self):
        """It should not create a Product without Content-Type"""
        response = self.client.post(BASE_URL, json={})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_create_product_bad_content_type(self):
        """It should not create a Product with bad Content-Type"""
        response = self.client.post(
            BASE_URL, json={}, content_type="text/plain"
        )
        self.assertEqual(
            response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

    def test_create_product_invalid_content_type(self):
        """It should not create a Product with an invalid Content-Type"""
        response = self.client.post(
            BASE_URL,
            json={"name": "Test"},
            content_type="text/html"
        )
        self.assertEqual(
            response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

    def test_create_product_no_header_content_type(self):
        """It should not create a Product with no Content-Type header"""
        response = self.client.post(BASE_URL, data="not json")
        self.assertEqual(
            response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )
