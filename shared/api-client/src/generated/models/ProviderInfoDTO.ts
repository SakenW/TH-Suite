/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ModelCapabilityDTO } from './ModelCapabilityDTO';
/**
 * Provider and model info.
 */
export type ProviderInfoDTO = {
    provider: string;
    model: string;
    capabilities: ModelCapabilityDTO;
    is_active?: boolean;
    description?: (string | null);
};

