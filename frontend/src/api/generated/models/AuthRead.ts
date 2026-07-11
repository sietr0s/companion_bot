/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Схема чтения учётной записи (для internal API).
 */
export type AuthRead = {
    id: string;
    identifier: string;
    identifier_type: string;
    hashed_password?: (string | null);
    role?: (string | null);
    created_at: string;
    updated_at: string;
};

