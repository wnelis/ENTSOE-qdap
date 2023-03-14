# ENTSOE-qdap
Query day-ahead prices from ENTSOE-E

This module is inspired on module entsoe-py. The latter module can retrieve much information about the production and distribution of electrical energy in Europe. As a consequence, module entsoe-py is rather large. It requiers more than 50 [MiB] python modules, such as pandas and numpy.

As the only needed function is to retrieve the prices of electrical energy and as this script is to run on a resource-constrainted machine, a Raspberry Pi
0W, module entsoe_qdap is developed, which basically implements only method EntsoeRawClient.query_day_ahead_prices from module entsoe-py.

Details of the REST API used in this module can be found at URL https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
