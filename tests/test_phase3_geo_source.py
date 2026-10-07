import json

from agriflow.data.sources.geo import GeographySource


class FakeGeoClient:
    def request_json(self, method, url, **kwargs):
        if 'geoboundaries.org/api/current' in url:
            return {'boundaryID':'IND-ADM1-test','boundaryYearRepresented':'2024','boundarySource':'Test',
                    'simplifiedGeometryGeoJSON':'https://example.test/india.geojson'}
        if url=='https://example.test/india.geojson':
            return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{'shapeName':'Test State'},'geometry':{'type':'Polygon','coordinates':[]}}]}
        raise AssertionError(url)


def test_geoboundaries_download_writes_provenance(tmp_path):
    target=tmp_path/'india_states.geojson'
    GeographySource(client=FakeGeoClient()).download_state_geojson(target,provider='geoboundaries')
    assert target.exists()
    meta=json.loads(target.with_suffix('.source.json').read_text())
    assert meta['provider']=='geoBoundaries gbOpen'
    assert 'CC BY 4.0' in meta['license']
