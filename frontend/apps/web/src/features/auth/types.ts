export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
}

export interface UpdateEmailRequest {
  email: string;
}

export interface UpdatePasswordRequest {
  current_password: string;
  new_password: string;
}
