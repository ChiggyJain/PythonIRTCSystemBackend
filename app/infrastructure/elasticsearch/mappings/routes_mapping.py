
ROUTES_INDEX_MAPPING = {
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
                    "tokenizer": "standard",
                    "filter": ["lowercase"]
                },
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
    },
    "mappings": {
        "properties": {
            "train_id": {
                "type": "keyword"
            },
            "train_number": {
                "type": "keyword",
            },
            "train_name": {
                "type": "text",
            },
            "routes" : {
                "type" : "nested",
                "properties" : {
                    "station_id" : {
                        "type" : "keyword",
                    },
                    "name" : {
                        "type" : "text",
                    },
                    "code" : {
                        "type" : "keyword",
                    },
                    "sequence_number" : {
                        "type" : "integer",
                    },
                    "arrival_time" : {
                        "type" : "keyword",
                    },
                    "departure_time" : {
                        "type" : "keyword",
                    },
                    "distance_from_origin" : {
                        "type" : "float",
                    }
                }
            },
            "schedules" : {
                "type" : "nested",
                "properties" : {
                    "id" : {
                        "type" : "keyword"
                    },
                    "departure_date" : {
                        "type" : "date"
                    },
                    "available" : {
                        "type" : "integer"
                    },
                    "locked" : {
                        "type" : "integer"
                    },
                    "booked" : {
                        "type" : "integer"
                    },
                    "status" : {
                        "type" : "keyword"
                    },
                }
            },
            "seatSummary" : {
                "properties": {
                    "total" : {
                        "type" : "integer"
                    },
                    "LOWER" : {
                        "type" : "integer"
                    },
                    "MIDDLE" : {
                        "type" : "integer"
                    },
                    "UPPER" : {
                        "type" : "integer"
                    },
                    "SIDE_LOWER" : {
                        "type" : "integer"
                    },
                    "SIDE_UPPER" : {
                        "type" : "integer"
                    }
                }
            }
        }
    }
}