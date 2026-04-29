
export interface User {
  id: number;
  name: string;
  phone_number: string | null;
  role: string | null;
  created_at: string;
}

export interface Call {
  id: number;
  audio_id: string | null;
  manager_id: number | null;
  manager_name: string | null;
  client_id: string | null;
  transcript: string | null;
  summary: string | null;
  start_time: string | null;
  duration_sec: number | null;
  status: string | null;
  task_id: string | null;
  created_at: string | null;
  provider: string | null;
  external_id: string | null;
  direction: string | null;
  from_number: string | null;
  to_number: string | null;
}

export interface SpeakerTurn {
  id: number;
  speaker: string | null;
  text: string | null;
  t_start: number | null;
  t_end: number | null;
}

export interface CheckResult {
  id: number;
  check_id: number;
  speaker_turn_id: number | null;
  value_boolean: boolean | null;
  value_score: number | null;
  value_category: string | null;
  raw_response: string | null;
}

export interface CallDetail extends Call {
  turns: SpeakerTurn[];
  results: CheckResult[];
}

export interface Check {
  id: number;
  name: string;
  description: string | null;
  scope: string | null;
  type: string | null;
  output_type: string | null;
  weight: number | null;
  active: boolean;
  rule_config: Record<string, unknown> | null;
  prompt: string | null;
  expected_format: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface IntegrationLog {
  id: number;
  provider: string;
  event_type: string | null;
  external_id: string | null;
  call_id: number | null;
  status: string; // received / processed / skipped / error
  message: string | null;
  payload: unknown | null;
  created_at: string | null;
}

export interface IntegrationStatus {
  webhook_configured: boolean;
  webhook_url: string;
  max_audio_mb: number;
}
