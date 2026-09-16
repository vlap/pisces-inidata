"""
Unit tests for pisces_inidata.woa23 module.
"""

import pytest
from pisces_inidata.woa23 import TRACER_LOOKUP, process_tracer


def test_tracer_lookup_aliases():
    assert TRACER_LOOKUP['n'][3] == 'NO3'
    assert TRACER_LOOKUP['no3'][3] == 'NO3'
    assert TRACER_LOOKUP['n_an'][3] == 'NO3'
    assert TRACER_LOOKUP['nitrate'][3] == 'NO3'

    assert TRACER_LOOKUP['p'][3] == 'PO4'
    assert TRACER_LOOKUP['po4'][3] == 'PO4'
    assert TRACER_LOOKUP['p_an'][3] == 'PO4'

    assert TRACER_LOOKUP['i'][3] == 'Si'
    assert TRACER_LOOKUP['si'][3] == 'Si'
    assert TRACER_LOOKUP['i_an'][3] == 'Si'

    assert TRACER_LOOKUP['o'][3] == 'O2'
    assert TRACER_LOOKUP['o2'][3] == 'O2'
    assert TRACER_LOOKUP['o_an'][3] == 'O2'


def test_invalid_tracer():
    with pytest.raises(ValueError, match="Unknown var_code"):
        process_tracer("invalid_var", "/dummy", "/dummy.nc")
