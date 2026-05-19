"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://161.35.192.56:8700";

interface AuthResponse {
  token: string;
  user: { id: string; email: string };
}

// Store token in localStorage
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("agentrecall_token");
}

function setToken(token: string) {
  localStorage.setItem("agentrecall_token", token);
}

function removeToken() {
  localStorage.removeItem("agentrecall_token");
}

export async function signUp(
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/v1/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Signup failed");
  }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function signIn(
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function getAccessToken(): Promise<string | null> {
  return getToken();
}

export async function getUser() {
  const token = getToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function signOut() {
  removeToken();
}

// API Key auth for agents
function getApiKeyFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("agentrecall_api_key");
}

export function storeApiKey(key: string) {
  localStorage.setItem("agentrecall_api_key", key);
}

export function getApiKey(): string | null {
  return getApiKeyFromStorage();
}

export async function isAuthenticated(): Promise<boolean> {
  const token = getToken();
  if (token) return true;
  const apiKey = getApiKeyFromStorage();
  return !!apiKey;
}

export async function loginWithApiKey(apiKey: string): Promise<void> {
  const res = await fetch(`${API_BASE}/v1/auth/api-key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "API key authentication failed");
  }
  const data = await res.json();
  // Store the JWT token returned from validation
  if (data.token) setToken(data.token);
  storeApiKey(apiKey);
}
