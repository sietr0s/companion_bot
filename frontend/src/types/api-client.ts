import type {
  AuthService,
  ClassifierService,
  HealthService,
  JobMatcherService,
  MediaService,
  NotificationsService,
  TelegramClientsService,
  UsersService,
} from '../api/generated';

export interface ApiClient {
  auth: typeof AuthService;
  classifier: typeof ClassifierService;
  health: typeof HealthService;
  jobMatcher: typeof JobMatcherService;
  media: typeof MediaService;
  notifications: typeof NotificationsService;
  telegram: typeof TelegramClientsService;
  users: typeof UsersService;
}
