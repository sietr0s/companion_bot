/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Вакансия, доступная администратору frontend.
 */
export type JobOfferAdminRead = {
    id: string;
    title: string;
    description?: (string | null);
    tags?: (Array<string> | null);
    salary_from?: (number | null);
    salary_to?: (number | null);
    location?: (string | null);
    source_chat_id: number;
    source_message_id: number;
    telegram_sender_id?: (number | null);
    telegram_username?: (string | null);
    telegram_first_name?: (string | null);
    telegram_last_name?: (string | null);
    category_ids?: (Array<string> | null);
    created_at: string;
    updated_at: string;
};

