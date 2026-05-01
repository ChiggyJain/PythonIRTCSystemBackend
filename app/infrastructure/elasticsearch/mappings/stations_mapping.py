# filepath: app/infrastructure/elasticsearch/mappings/station_mapping.py

STATIONS_INDEX_MAPPING = {

    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "autocomplete_tokenizer",
                    "filter": ["lowercase"]
                },
                "search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standar",
                    "filter": ["lowercase"]
                },
                "tokenizer": {
                    "autocomplete_tokenizer": {
                        "type": "edge_ngram",
                        "min_gram" : 2,
                        "max_gram" : 20,
                        "token_chars" : ["letter", "digit"]
                    },
                }
            }
        }
    },

    "mappings": {
        "properties": {
            "station_id": {
                "type": "keyword",
            },
            "name": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "search_analyzer": "search_analyzer",
            },
            "code": {
                "type": "keyword",
            },
            "city": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "search_analyzer": "search_analyzer",
            },
            "sugggest": {
                "type": "completion"
            }
        }
    }
}