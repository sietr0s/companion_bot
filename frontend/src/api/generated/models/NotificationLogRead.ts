/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Лог отправки уведомления.
 */
export type NotificationLogRead = {
    id: string;
    auth_id: string;
    channel: string;
    template_name: string;
    recipient: string;
    subject?: (string | null);
    body: string;
    status: string;
    error_message?: (string | null);
    created_at: string;
    updated_at: string;
};

