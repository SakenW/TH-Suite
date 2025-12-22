export type TenantCreateDTO = {
    name: string;
    plan_id?: (string | null);
    settings?: (Record<string, any> | null);
};
