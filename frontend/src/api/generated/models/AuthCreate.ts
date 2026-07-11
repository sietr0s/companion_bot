/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Запрос на создание учётной записи (internal).
 */
export type AuthCreate = {
    identifier: string;
    identifier_type: 'email' | 'phone' | 'telegram';
    hashed_password: string;
    role?: (string | null);
};

