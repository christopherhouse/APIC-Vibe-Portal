"""Unit tests for the AI Search index schema builder."""

from __future__ import annotations

from indexer.index_schema import INDEX_NAME, build_index_schema


class TestBuildIndexSchema:
    def test_returns_index_with_correct_name(self) -> None:
        schema = build_index_schema()
        assert schema.name == INDEX_NAME

    def test_accepts_custom_index_name(self) -> None:
        schema = build_index_schema(index_name="my-custom-index")
        assert schema.name == "my-custom-index"

    def test_has_id_key_field(self) -> None:
        schema = build_index_schema()
        fields = {f.name: f for f in schema.fields}
        assert "id" in fields
        assert fields["id"].key is True

    def test_has_all_required_fields(self) -> None:
        schema = build_index_schema()
        field_names = {f.name for f in schema.fields}
        required = {
            "id",
            "apiName",
            "title",
            "description",
            "kind",
            "lifecycleStage",
            "versions",
            "contacts",
            "tags",
            "customProperties",
            "specContent",
            "parentApiId",
            "chunkIndex",
            "createdAt",
            "updatedAt",
            "contentVector",
        }
        assert required.issubset(field_names)

    def test_content_vector_has_correct_dimensions(self) -> None:
        schema = build_index_schema(embedding_dimensions=1536)
        fields = {f.name: f for f in schema.fields}
        assert fields["contentVector"].vector_search_dimensions == 1536

    def test_content_vector_dimensions_can_be_overridden(self) -> None:
        schema = build_index_schema(embedding_dimensions=3072)
        fields = {f.name: f for f in schema.fields}
        assert fields["contentVector"].vector_search_dimensions == 3072

    def test_has_semantic_search_config(self) -> None:
        schema = build_index_schema()
        assert schema.semantic_search is not None
        configs = schema.semantic_search.configurations
        assert configs is not None
        assert len(configs) == 1

    def test_semantic_config_title_field_is_title(self) -> None:
        schema = build_index_schema()
        config = schema.semantic_search.configurations[0]
        assert config.prioritized_fields.title_field.field_name == "title"

    def test_semantic_config_has_content_fields(self) -> None:
        schema = build_index_schema()
        config = schema.semantic_search.configurations[0]
        content_field_names = [f.field_name for f in config.prioritized_fields.content_fields]
        assert "description" in content_field_names
        assert "specContent" in content_field_names

    def test_semantic_config_has_keyword_fields(self) -> None:
        schema = build_index_schema()
        config = schema.semantic_search.configurations[0]
        keyword_field_names = [f.field_name for f in config.prioritized_fields.keywords_fields]
        assert "apiName" in keyword_field_names
        assert "tags" in keyword_field_names

    def test_has_vector_search_config(self) -> None:
        schema = build_index_schema()
        assert schema.vector_search is not None
        assert len(schema.vector_search.algorithms) == 1
        assert len(schema.vector_search.profiles) == 1

    def test_filterable_fields(self) -> None:
        schema = build_index_schema()
        fields = {f.name: f for f in schema.fields}
        assert fields["kind"].filterable is True
        assert fields["lifecycleStage"].filterable is True
        assert fields["tags"].filterable is True
        assert fields["parentApiId"].filterable is True
        assert fields["chunkIndex"].filterable is True

    def test_facetable_fields(self) -> None:
        schema = build_index_schema()
        fields = {f.name: f for f in schema.fields}
        assert fields["kind"].facetable is True
        assert fields["lifecycleStage"].facetable is True
        assert fields["tags"].facetable is True

    def test_sortable_fields(self) -> None:
        schema = build_index_schema()
        fields = {f.name: f for f in schema.fields}
        assert fields["apiName"].sortable is True
        assert fields["title"].sortable is True
        assert fields["createdAt"].sortable is True
        assert fields["updatedAt"].sortable is True
        assert fields["chunkIndex"].sortable is True

    def test_spec_content_not_filterable_sortable_facetable(self) -> None:
        """specContent must not be filterable/sortable/facetable to avoid
        Lucene term-too-large errors on large spec content.
        """
        schema = build_index_schema()
        fields = {f.name: f for f in schema.fields}
        assert fields["specContent"].filterable is False
        assert fields["specContent"].sortable is False
        assert fields["specContent"].facetable is False

    def test_has_suggester(self) -> None:
        schema = build_index_schema()
        assert schema.suggesters is not None
        assert len(schema.suggesters) == 1

    def test_suggester_name_is_sg(self) -> None:
        schema = build_index_schema()
        suggester = schema.suggesters[0]
        assert suggester.name == "sg"

    def test_suggester_source_fields(self) -> None:
        schema = build_index_schema()
        suggester = schema.suggesters[0]
        assert "apiName" in suggester.source_fields
        assert "title" in suggester.source_fields
        assert "description" in suggester.source_fields
