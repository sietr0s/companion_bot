import type {
  AuthService,
  ClassifierService,
  HealthService,
  InternalService,
  MediaService,
  NotificationsService,
  TelegramClientsService,
  UsersService,
} from '../api/generated';

export interface ApiClient {
  auth: typeof AuthService;
  classifier: typeof ClassifierService;
  health: typeof HealthService;
  internal: typeof InternalService;
  media: typeof MediaService;
  notifications: typeof NotificationsService;
  telegram: typeof TelegramClientsService;
  users: typeof UsersService;
}