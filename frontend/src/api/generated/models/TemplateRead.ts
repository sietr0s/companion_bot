/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Просмотр шаблона.
 */
export type TemplateRead = {
    id: string;
    name: string;
    channel: string;
    subject_template?: (string | null);
    body_template: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
};

