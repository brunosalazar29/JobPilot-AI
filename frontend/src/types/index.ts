export type ID = number;

export type Profile = {
  id: ID;
  user_id: ID;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  experience_summary: string | null;
  skills: string[];
  languages: string[];
  seniority: string | null;
  target_roles: string[];
  preferred_modality: string | null;
  salary_expectation: number | null;
  salary_currency: string | null;
  field_sources: Record<string, string>;
  missing_fields: string[];
  recommendations: Array<Record<string, string>>;
  profile_completeness: number;
};

export type DetectedProfileField = {
  key: string;
  label: string;
  value: string | number | string[] | null;
  source: "cv" | "inferred" | "user_input" | "missing" | "unknown";
  status: "detected" | "inferred" | "user_input" | "missing" | "pending_confirmation";
  useful_for: string;
  needs_confirmation: boolean;
};

export type DetectedProfile = {
  profile: Profile;
  fields: DetectedProfileField[];
  missing_fields: string[];
  recommendations: Array<{
    field: string;
    label: string;
    severity: string;
    message: string;
    reason: string;
  }>;
  completeness: number;
  latest_resume: {
    id: ID;
    filename: string;
    status: string;
    parsed_at: string | null;
    error_message: string | null;
  } | null;
};

export type Resume = {
  id: ID;
  original_filename: string;
  storage_path: string;
  content_type: string | null;
  status: string;
  parsed_at: string | null;
  error_message: string | null;
  parsed_resume?: {
    skills: string[];
    languages: string[];
    work_experience: Array<Record<string, unknown>>;
  } | null;
  created_at: string;
};

export type Job = {
  id: ID;
  title: string;
  company: string;
  location: string | null;
  seniority: string | null;
  remote_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  technologies: string[];
  language_requirements: string[];
  description: string;
  url: string | null;
  created_at: string;
};

export type JobMatch = {
  id: ID;
  job_id: ID;
  resume_id: ID | null;
  score: number;
  summary: string | null;
  criteria: Record<string, number>;
  missing_keywords: string[];
  job?: Job | null;
};

export type Application = {
  id: ID;
  job_id: ID | null;
  resume_id: ID | null;
  company: string;
  position: string;
  url: string | null;
  score: number | null;
  status: string;
  generated_responses: Record<string, string>;
  document_refs: Array<Record<string, unknown>>;
  logs: Array<Record<string, unknown>>;
  errors: string | null;
  created_at: string;
  job?: Job | null;
};

export type TaskRun = {
  id: ID;
  task_name: string;
  celery_task_id: string | null;
  status: string;
  progress: number;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  logs: Array<Record<string, unknown>>;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};
