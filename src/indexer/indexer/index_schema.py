"""Azure AI Search index schema definition.

Defines the search index fields, semantic search configuration, and
vector search configuration used by the APIC Vibe Portal to enable
hybrid (keyword + semantic + vector) API discovery.
"""

from __future__ import annotations

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchSuggester,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDEX_NAME = "apic-apis"

_VECTOR_PROFILE_NAME = "apic-hnsw-profile"
_VECTOR_ALGORITHM_NAME = "apic-hnsw"
_SEMANTIC_CONFIG_NAME = "apic-semantic-config"
_SUGGESTER_NAME = "sg"


def build_index_schema(index_name: str = INDEX_NAME, embedding_dimensions: int = 1536) -> SearchIndex:
    """Return a :class:`SearchIndex` describing the APIC APIs search index.

    Parameters
    ----------
    index_name:
        Name of the search index to create or update.
    embedding_dimensions:
        Number of dimensions in the content embedding vector.
        Must match the Azure OpenAI model used for indexing (1536 for
        ``text-embedding-ada-002``).
    """
    fields: list[SearchField] = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchField(
            name="apiName",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            sortable=True,
        ),
        SearchField(
            name="description",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="kind",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="lifecycleStage",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="versions",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
        ),
        SearchField(
            name="contacts",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
        ),
        SearchField(
            name="tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="customProperties",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="specContent",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=False,
            sortable=False,
            facetable=False,
        ),
        SearchField(
            name="parentApiId",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchField(
            name="chunkIndex",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="createdAt",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="updatedAt",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=embedding_dimensions,
            vector_search_profile_name=_VECTOR_PROFILE_NAME,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name=_VECTOR_ALGORITHM_NAME),
        ],
        profiles=[
            VectorSearchProfile(
                name=_VECTOR_PROFILE_NAME,
                algorithm_configuration_name=_VECTOR_ALGORITHM_NAME,
            ),
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=_SEMANTIC_CONFIG_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[
                        SemanticField(field_name="description"),
                        SemanticField(field_name="specContent"),
                    ],
                    keywords_fields=[
                        SemanticField(field_name="apiName"),
                        SemanticField(field_name="tags"),
                    ],
                ),
            ),
        ],
    )

    suggesters: list[SearchSuggester] = [
        SearchSuggester(
            name=_SUGGESTER_NAME,
            source_fields=["apiName", "title", "description"],
        ),
    ]

    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
        suggesters=suggesters,
    )
