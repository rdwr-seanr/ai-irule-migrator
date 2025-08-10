def test_placeholder():
    assert True

from packages.tools.irule_parser import parse_irule

SAMPLE = """when HTTP_REQUEST {
    HTTP::header replace Location https://example.com
}"""

def test_parse_irule_events():
    parsed = parse_irule(SAMPLE)
    ast = parsed['ast']
    assert ast['events'], 'Should detect at least one event'
    assert ast['events'][0]['name'] == 'HTTP_REQUEST'
