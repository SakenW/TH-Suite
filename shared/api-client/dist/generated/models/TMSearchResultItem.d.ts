export type TMSearchResultItem = {
    tm_id: string;
    source_text: string;
    target_text: string;
    similarity: number;
    origin?: (string | null);
};
