
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
            "train_id": {
                "type": "integer",
                "index": True
            },
            "train_name": {
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
            "train_number": {
                "type": "keyword",
                "normalizer": "lowercase"
            }
        }
    }
}