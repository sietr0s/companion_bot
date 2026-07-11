/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Запрос на обновление учётной записи (internal).
 */
export type AuthUpdate = {
    identifier?: (string | null);
    identifier_type?: ('email' | 'phone' | 'telegram' | null);
    hashed_password?: (string | null);
    role?: (string | null);
};

