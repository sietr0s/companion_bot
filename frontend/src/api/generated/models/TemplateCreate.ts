/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Создание шаблона уведомления.
 */
export type TemplateCreate = {
    /**
     * Название шаблона
     */
    name: string;
    /**
     * Канал отправки (email, sms, push)
     */
    channel: string;
    subject_template?: (string | null);
    /**
     * Тело шаблона (Jinja2)
     */
    body_template: string;
    is_active?: boolean;
};

