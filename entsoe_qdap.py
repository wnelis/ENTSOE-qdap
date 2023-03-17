#
# Module entsoe-qdap.py can retrieves the prices for electrical energy the next
# day. It returns a dictionary with the key being the time stamp of the start of
# a period and the value the price during that period.
#
# This module is inspired on module entsoe-py. The latter module can retrieve
# much information about the production and distribution of electrical energy in
# Europe. As a consequence, module entsoe-py is rather large. It requiers more
# than 50 [MiB] python modules, such as pandas and numpy.
# As the only needed function is to retrieve the prices of electrical energy and
# as this script is to run on a resource-constrainted machine, a Raspberry Pi
# 0W, module entsoe_qdap is developed, which basically implements only method
# EntsoeRawClient.query_day_ahead_prices from module entsoe-py.
#
# Details of the REST API used in this module can be found at URL
# https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
#
# Written by W.J.M. Nelis, wim.nelis@ziggo.nl, 2023.03
#
import calendar				# Inverse of time.gmtime
from lxml import etree			# Parse XML document
import re				# Recognise and parse strings
import requests				# Https GET method
import time


#
# Constant definitions.
# ---------------------
#
base_url= 'https://web-api.tp.entsoe.eu/api'
document_type= 'A44'			# Request a price document
domain  = '10YNL----------L'		# The Netherlands
xmlns_id= 'entsoe'			# XML default name space identifier

# The time stamps found in the XML document are all UTC times. Define their
# structure, which is needed to parse them.
one_day    = 86400			# Seconds per day
time_fmt_0 = '%Y%m%d%H00'		# Format to create UTC time string
time_fmt_1 = '%Y-%m-%dT%H:%MZ'		# Format to parse UTC time string

# The resolution in the XML document can be expressed in various units. The unit
# of the resolution is changed to [s], to ease the computations.
reso_format= re.compile( r'^PT(\d+)([SMH])$' )  # See REST API
reso_multif= { 'S': 1, 'M': 60, 'H': 3600 }

# Define the scalar fields to be extracted from the XML document. If a value is
# specified, the named field must have the given value. If the field is missing
# or if the value is different, an exception is raised. If clean-up is specified
# for a field, the field is removed from the result area.
xml_extract= {
 # Key           XML path                               Value  Clean-up
  'doc_type': ( 'type'                                , 'A44', True  ),
  'curv_typ': ( 'TimeSeries/curveType'                , 'A01', True  ),
  'unit_cur': ( 'TimeSeries/currency_Unit.name'       , 'EUR', True  ),
  'unit_pmu': ( 'TimeSeries/price_Measure_Unit.name'  , None , True  ),
  'sop'     : ( 'TimeSeries/Period/timeInterval/start', None , False ),
  'eop'     : ( 'TimeSeries/Period/timeInterval/end'  , None , False ),
  'reso'    : ( 'TimeSeries/Period/resolution'        , None , False )
}


class entsoeException( Exception ):
  pass

class entsoe():

  def __init__( self, web_key: str, time_out: int= None ):
    assert web_key is not None, 'Illegal web API key'
    self.webkey = web_key
    self.timeout= time_out

 #
 # Private method _add_prefix adds the default name space identifier to each
 # unprefixed node name.
 #
  def _add_prefix( self, rp: str, nsi: str ) -> str:
    if nsi is None:  return rp
    if nsi == ''  :  return rp
  #
    levels= rp.split( '/' )
    for i,level in enumerate(levels):
      if not ':' in level:  levels[i]= f'{nsi}:{level}'
    return '/'.join( levels )

 #
 # Private method _base_request issue a GET request and returns the response.
 #
  def _base_request( self, payload: dict ) -> requests.Response:
    r= requests.get( base_url, params=payload )
    try:
      r.raise_for_status()
    except Exception:
      raise
    else:
  # ENTSO-E has changed their server to also respond with 200 if there is no
  # data but all parameters are valid. This means we need to check the contents
  # for this error even when status code 200 is returned. To prevent parsing the
  # full response, do a text matching instead of full parsing. Also only do this
  # when response type content is text and not for example a zip file.
      if r.headers.get('content-type', '') == 'application/xml':
        if 'No matching data found' in r.text:
          raise entsoeException( 'No matching data found' )
  #
      return r

 #
 # Private method _reso_s takes a string describing the resolution. It returns
 # the resolution expressed in seconds as an integer. If the conversion fails,
 # it returns None.
 #
  def _reso_s( self, step: str ) -> int:
    mo= reso_format.match( step )
    if mo is None:
      raise entsoeException( f'Unrecognised resolution: {step}' )
    else:
      rv= mo.group( 1 )			# Resolution value
      ru= mo.group( 2 )			# Resolution unit
      if ru in reso_multif:
        return int(rv)*reso_multif[ru]
      else:
        raise entsoeExeption( f'Unrecognised unit in resolution: {step}' )

 #
 # Private method _ts_last_midnight returns the time stamp, the integer number
 # of seconds since epoch, of the last midnight. That is the time stamp of
 # 00:00:00 today, local time, is returned.
 #
  @staticmethod
  def _ts_last_midnight() -> int:
    now= int( time.time() )		# Current time
    ts = time.localtime( now )		# Determine local time in day
    return now - ts.tm_hour*3600 - ts.tm_min*60 - ts.tm_sec

 #
 # Private method _ts_utc converts a time stamp, an integer number, to a string
 # containing the current time in UTC, formatted as specified in the REST API.
 #
  @staticmethod
  def _ts_utc( ts: int ) -> str:
    ts= time.gmtime( ts )		# Convert to struct_time, in UTC
    return time.strftime( time_fmt_0, ts )	# Convert to string

 #
 # Private method _utc_ts converts a string containing a time in time zone
 # UTC. It returns the equivalent time stamp, an integer number. If the
 # conversion fails, it returns None.
 #
  @staticmethod
  def _utc_ts( utc_time: str ) -> int:
    try:
      ts= time.strptime( utc_time, time_fmt_1 )	# Convert to struct_time
    except Exception as e:
      raise entsoeException( f'{e}' )
    else:
      return calendar.timegm( ts )	# Convert to integer time stamp

 #
 # Private method _parse_xml_response checks and parses the xml formatted
 # response. Any error causes an exception to be thrown. In case no errors are
 # found, the fields of interest are extracted and retuned bundled in a dict.
 #
  def _parse_xml_response( self, xmldoc ):
    global xmlns_id
    result= { 'epl': {} }		# Preset result area
    root= etree.fromstring( xmldoc )	# Build tree and get root
  #
    ns= {}				# Create name space dictionary
    for k,v in root.nsmap.items():
      if k is None:  ns[xmlns_id]= v	# Save default name space
    if not ns:  xmlns_id= None		# Clear id if no default name space
  #
    for k in xml_extract:
      fp= xml_extract[k]		# Fetch field parameters
      xp= self._add_prefix( fp[0], xmlns_id )	# Build absolute path
      v = root.find( xp, ns )
      if v is None:
        raise entsoeException( f'Unknown field: {fp[0]}' )
      v = v.text			# Fetch field value
      if fp[1] is not None:
        if v != fp[1]:
          raise entsoeException( f'Unexpected value: {fp[0]} = {v}' )
      result[k]= v
  #
    unit= f'{result["unit_cur"]}/{result["unit_pmu"]}'
    if unit.endswith('WH'):  unit= unit[:-1] + 'h'
    result['unit']= unit
  #
    result['sop' ]= self._utc_ts( result['sop' ] )
    result['eop' ]= self._utc_ts( result['eop' ] )
    result['reso']= self._reso_s( result['reso'] )
  #
    point= self._add_prefix( 'TimeSeries/Period/Point', xmlns_id )
    index= self._add_prefix( 'position', xmlns_id )
    price= self._add_prefix( 'price.amount', xmlns_id )
    lop  = root.findall( point, ns )
    for k in lop:
      vi= int  ( k.find(index,ns).text )
      vp= float( k.find(price,ns).text )
      vt= result['sop'] + (vi-1)*result['reso']
      result['epl'][vt]= vp
  #
    for k in xml_extract:
      if xml_extract[k][2]:		# Check clean-up flag
        if k in result:  del result[k]
  #
    return result

 #
 # Private method _query_prices takes the start time and the end time of a
 # period and requests the electricity prices for that period.
 #
  def _query_prices( self, sop: str, eop: str ):
    payload= {
      'documentType' : document_type,
      'in_Domain'    : domain,
      'out_Domain'   : domain,
      'securityToken': self.webkey,
      'periodStart'  : sop,
      'periodEnd'    : eop
    }
    r= self._base_request( payload )
# Check r.headers["content-type"] == 'text/xml'
    return self._parse_xml_response( r.text.encode() )

 #
 # Method query_today_prices requests the electricity prices for today, from
 # 00:00 up to tomorrow 00:00. The times are expressed in the local time-zone.
 #
  def query_today_prices( self ):
    tlm= self._ts_last_midnight()	# Time stamp of last midnight
    sop= self._ts_utc( tlm )		# Start of period
    eop= self._ts_utc( tlm+one_day )	# End of period
    return self._query_prices( sop, eop )

 #
 # Method query_day_ahead_prices requests the electricity proces for tomorrow,
 # from 00:00 until the day after tomorrow 00:00, all in the local time-zone.
 #
  def query_day_ahead_prices( self ):
    tnm= self._ts_last_midnight() + one_day	# Time stamp of next midnight
    sop= self._ts_utc( tnm )		# Start of period
    eop= self._ts_utc( tnm+one_day )	# End of period
    return self._query_prices( sop, eop )
