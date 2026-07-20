/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Подписка пользователя, доступная администратору frontend.
 */
export type SubscriptionAdminRead = {
    id: string;
    auth_id: string;
    keywords?: (Array<string> | null);
    category_ids?: (Array<string> | null);
    min_salary?: (number | null);
    max_salary?: (number | null);
    locations?: (Array<string> | null);
    is_active: boolean;
    created_at: string;
    updated_at: string;
};

