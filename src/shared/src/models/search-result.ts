/**
 * A facet (filter category) returned by search.
 */
export interface SearchFacet {
  field: string;
  values: SearchFacetValue[];
}

/**
 * An individual facet value with count.
 */
export interface SearchFacetValue {
  value: string;
  count: number;
}

/**
 * Collection of facets from a search response.
 */
export interface SearchFacets {
  facets: SearchFacet[];
}

/**
 * Generic search result wrapper. T is the type of individual result items.
 */
export interface SearchResult<T> {
  items: T[];
  totalCount: number;
  facets?: SearchFacets;
  queryDuration: number;
}
