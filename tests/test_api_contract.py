import unittest

from app import app


class ApiContractTest(unittest.TestCase):
    def test_dashboard_routes_are_registered(self) -> None:
        routes = {route.path for route in app.routes}
        self.assertTrue(
            {
                "/api/filters",
                "/api/overview",
                "/api/trends",
                "/api/regions",
                "/api/growth",
                "/api/products",
                "/api/why",
                "/api/trades",
                "/api/models/{model_name}",
                "/api/story",
            }.issubset(routes)
        )


if __name__ == "__main__":
    unittest.main()
