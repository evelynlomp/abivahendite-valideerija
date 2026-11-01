import sys
sys.path.insert(0, '.')
from src.restriction_engine import RestrictionEngine



def test_zinc_oxide_rules():
    # 1. Product with zinc -> valid
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.18", "Abena tsinksalv 100ml", "ABENA TSINKSALV 100ML", "nahahooldusvahend")
    assert ok is True
    assert msg is None

    # 2. Product without zinc (regular barrier cream / lotion) -> invalid under 09.21.18!
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.18", "Seni Care kaitsekreem arginiiniga 200ml", "SENI CARE KAITSEKREEM", "nahahooldusvahend")
    assert ok is False
    assert rule == "ZINC_OXIDE_REQUIRED"
    assert "AINULT tsinkoksiidi põhised vahendid" in msg

    # 3. Molicare Skin tsinkoksiidiga kaitsevaht -> valid
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.18", "MoliCare Skin kaitsevaht tsinkoksiidiga 100ml", "MOLICARE SKIN KAITSEVAHT", "nahahooldusvahend")
    assert ok is True


def test_wash_rules():
    # 1. Shower gel -> invalid under 09.21.06
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.06", "Tena dušigeel 500ml", "TENA DUŠIGEEL", "nahapesuvahend")
    assert ok is False
    assert rule == "EXCLUDED_WASH_PRODUCT"
    assert "dušigeelid ja dušiõlid" in msg

    # 2. Shampoo -> invalid under 09.21.06
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.06", "Abena juuksešampoon 250ml", "ABENA ŠAMPOON", "nahapesuvahend")
    assert ok is False
    assert rule == "EXCLUDED_WASH_PRODUCT"

    # 3. Waterless wash mousse / cream -> valid
    ok, msg, rule = RestrictionEngine.check_restrictions("09.21.06", "Tena Wash Mousse veevaba pesuvaht 400ml", "TENA WASH MOUSSE", "veevaba pesuvahend")
    assert ok is True


def test_threshold_ramp_rules():
    # 1. Threshold ramp -> invalid under 18.30.15
    ok, msg, rule = RestrictionEngine.check_restrictions("18.30.15", "Kaldtee lävepakule 4 cm alumiinium", "KALDTEE LÄVEPAKULE", "kaldtee")
    assert ok is False
    assert rule == "EXCLUDED_THRESHOLD_RAMP"
    assert "lävepaku kaldteed" in msg

    # 2. Normal portable telescopic ramp -> valid
    ok, msg, rule = RestrictionEngine.check_restrictions("18.30.15", "Teleskoopne teisaldatav kaldtee 200 cm", "TEISALDATAV KALDTEE", "kaldtee")
    assert ok is True


def test_bed_tables_and_mattresses():
    # Bed cabinet -> invalid under 18.03.15
    ok, msg, rule = RestrictionEngine.check_restrictions("18.03.15", "Voodikapp ratastel sahtliga", "VOODIKAPP", "mööbel")
    assert ok is False
    assert rule == "EXCLUDED_BED_TRAY_OR_CABINET"

    # Standard foam mattress -> invalid under 04.33.06.01
    ok, msg, rule = RestrictionEngine.check_restrictions("04.33.06.01", "Standardne poroloonmadrats 90x200", "POROLOONMADRATS", "madrats")
    assert ok is False
    assert rule == "EXCLUDED_STANDARD_FOAM"

    # Profiled pressure-relieving mattress -> valid
    ok, msg, rule = RestrictionEngine.check_restrictions("04.33.06.01", "Lamatisi ennetav sektsioonmadrats Novacare", "NOVACARE MADRATS", "lamatiste madrats")
    assert ok is True


test_zinc_oxide_rules()
test_wash_rules()
test_threshold_ramp_rules()
test_bed_tables_and_mattresses()
print("All restriction engine unit tests passed successfully!")

