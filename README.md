# Query day-ahead prices from ENTSOE-E

## Description
This module is inspired on module entsoe-py. The latter module can retrieve much information about the production and distribution of electrical energy in Europe. As a consequence, module entsoe-py is rather large. It requiers more than 50 [MiB] python modules, such as pandas and numpy.

As the only needed function is to retrieve the prices of electrical energy and as this script is to run on a resource-constrainted machine, a Raspberry Pi
0W, module entsoe_qdap is developed, which basically implements only method EntsoeRawClient.query_day_ahead_prices from module entsoe-py.

Details of the REST API used in this module can be found at URL https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html

## Key
For API access from a script, a key is needed. This key can be requested at the ENTSOE-E transparancy platform. Obtaining the request takes two steps:

A) Go to https://transparency.entsoe.eu/dashboard/show, and register on the ENTSOE-E transparancy platform by clicking 'login' at the top right of the page.

B) Request an API web key by sending an email to transparency@entsoe.eu with “Restful API access” in the subject line. In the email body state your registered email address. You will receive an email describing how to generate the key.


