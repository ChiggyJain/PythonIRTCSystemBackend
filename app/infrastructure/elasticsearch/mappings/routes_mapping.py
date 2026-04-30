
ROUTES_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "station_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "station_id": {
                "type": "integer",
                "index": True
            },
            "name": {
                "type": "text",
                "analyzer": "station_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    },
                    "suggest": {
                        "type": "completion"
                    }
                }
            },
            "code": {
                "type": "keyword",
                "normalizer": "lowercase"
            },
            "city": {
                "type": "keyword",
                "normalizer": "lowercase"
            },
            "state": {
                "type": "keyword",
                "normalizer": "lowercase"
            }
        }
    }
}