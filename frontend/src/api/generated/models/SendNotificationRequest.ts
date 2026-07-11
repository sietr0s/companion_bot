/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Запрос на отправку уведомления (internal).
 */
export type SendNotificationRequest = {
    auth_id: string;
    /**
     * Имя шаблона
     */
    template_name: string;
    /**
     * Канал отправки (email, sms, push)
     */
    channel?: string;
    /**
     * Данные для рендера шаблона
     */
    body?: Record<string, any>;
};

