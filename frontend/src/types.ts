export interface Option {
  id: string;
  text: string;
}

export type PollStatus = "active" | "expired";

export interface PollSummary {
  id: string;
  code: string;
  question: string;
  options: Option[];
  createdAt: string;
  expiresAt: string;
}

export interface PublicPoll {
  code: string;
  question: string;
  options: Option[];
  status: PollStatus;
  expiresAt: string;
}

export interface OptionTally {
  id: string;
  text: string;
  votes: number;
  percentage: number;
}

export interface ResultsPayload {
  type: "results";
  code: string;
  question: string;
  options: OptionTally[];
  totalVotes: number;
  status: PollStatus;
  crowdPulse: string;
}

export interface JoinResponse {
  voterId: string;
  nickname: string;
  code: string;
  question: string;
  options: Option[];
  expiresAt: string;
}
