import pytest
from src.agent.nodes import grade_query, should_rewrite
from src.agent.state import AgentState

def test_grade_query_in_scope():
   state = {"query": "What are BaFin requirements for AI?",
            "rewritten_query":"",
            "doc_types":[],
            "chunks":[],
            "generation":"",
            "rewrite_count":0,
            "documents_relevant":False
            }
   result = grade_query(state)
   assert result == "retrieve"


def test_grade_query_out_of_scope():
   state = {"query": "What are the advantages of AI?",
            "rewritten_query":"",
            "doc_types":[],
            "chunks":[],
            "generation":"",
            "rewrite_count":0,
            "documents_relevant":False
            }
   result = grade_query(state)
   assert result == "out_of_scope"


def test_should_rewrite():
   state = {"query":"What are BaFin requirements for AI?",
            "rewritten_query":"",
            "doc_types":[],
            "chunks":[],
            "generation":"",
            "rewrite_count":0,
            "documents_relevant":True
            }
   result = should_rewrite(state)
   assert result == "generate"


def test_should_rewrite_max():
   state = {"query":"What are BaFin requirements for AI?",
            "rewritten_query":"",
            "doc_types":[],
            "chunks":[],
            "generation":"",
            "rewrite_count":0,
            "documents_relevant":False
            }
   result = should_rewrite(state)
   assert result == "rewrite"

