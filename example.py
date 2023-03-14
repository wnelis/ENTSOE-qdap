#
# This demonstration program retrieves the prices for electricity tomorrow
# in the Netherlands.
#
import entsoe_qdap			# entsoe, query day ahead prices
import time

webkey= 'your-web-key'
now   = int( time.time() )
client= entsoe_qdap.entsoe( web_key= webkey, time_out= 10 )
try:
  dap= client.query_day_ahead_prices()
except Exception as e:
  print( f'Error: {e.value}' )
else:
  print( f'Current time: {now}' )
  print( f'Day ahead prices\n{dap}' )

