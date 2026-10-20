import datetime

from core.tools.find_transit_trips import FindTransitTripsArgs, FindTransitTripsTool
from core.tools.get_opening_hours import GetOpeningHoursArgs, GetOpeningHoursTool
from core.tools.lookup_price import LookupPriceArgs, LookupPriceTool
from core.tools.search_attractions import SearchAttractionsArgs, SearchAttractionsTool


def test_search_attractions():
    tool = SearchAttractionsTool()
    # Search for "museum" in Amsterdam
    res = tool.execute(SearchAttractionsArgs(city="Amsterdam", query="museum"))
    assert len(res) > 0
    assert any("Rijksmuseum" in v.name for v in res)
    assert any("Van Gogh" in v.name for v in res)

def test_get_opening_hours():
    tool = GetOpeningHoursTool()
    # Test for Louvre which is closed on Tuesdays (day 1)
    res = tool.execute(GetOpeningHoursArgs(venue_id="par-louvre", date="2024-06-18"))
    assert res.venue_id == "par-louvre"
    assert res.open_time == datetime.time(9, 0)
    assert res.close_time == datetime.time(18, 0)
    assert 1 in res.closure_days

def test_find_transit_trips():
    tool = FindTransitTripsTool()
    # Find trip from AMS-CS to BER-HBF after 08:00
    res = tool.execute(FindTransitTripsArgs(
        from_stop="AMS-CS", 
        to_stop="BER-HBF", 
        depart_after="2024-06-18T08:00:00"
    ))
    assert len(res) > 0
    assert res[0].trip_id == "IC-141"
    assert res[0].depart_at == datetime.datetime(2024, 6, 18, 9, 0)
    
def test_lookup_price_venue():
    tool = LookupPriceTool()
    # Lookup price for Rijksmuseum
    res = tool.execute(LookupPriceArgs(item_id="ams-rijksmuseum", category="adult"))
    assert res is not None
    assert res.amount == 22.50
    assert res.currency == "EUR"
    
def test_lookup_price_transit():
    tool = LookupPriceTool()
    # Lookup price for IC-141
    res = tool.execute(LookupPriceArgs(item_id="IC-141", category="adult"))
    assert res is not None
    assert res.amount == 69.90
    assert res.currency == "EUR"

def test_lookup_price_unknown():
    tool = LookupPriceTool()
    res = tool.execute(LookupPriceArgs(item_id="unknown-item", category="adult"))
    assert res is None
