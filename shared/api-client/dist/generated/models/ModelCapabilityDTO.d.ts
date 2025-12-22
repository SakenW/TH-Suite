/**
 * Model capability details.
 */
export type ModelCapabilityDTO = {
    supports_system_prompt: boolean;
    context_window: number;
    max_output_tokens?: (number | null);
    billing_unit?: string;
};
