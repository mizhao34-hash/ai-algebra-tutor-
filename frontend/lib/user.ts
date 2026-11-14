"use client";

// The only "auth" is a user id kept in the browser (CLAUDE.md: no real auth).
import { useEffect, useState } from "react";

const KEY = "tutor-user-id";
// Same rule as the backend's UserId path parameter.
export const USER_ID_PATTERN = /^[A-Za-z0-9_-]{1,40}$/;

// localStorage can throw (private mode, blocked storage), so every access is guarded.
function read(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function saveUserId(id: string | null) {
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* ignore: the id just won't be remembered */
  }
}

/** Returns [userId, loaded]. `loaded` is false until we've checked storage,
 *  so pages don't redirect before the saved id has been read. */
export function useUserId(): [string | null, boolean] {
  const [id, setId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    // Runs only in the browser; localStorage doesn't exist during server rendering.
    setId(read());
    setLoaded(true);
  }, []);
  return [id, loaded];
}
