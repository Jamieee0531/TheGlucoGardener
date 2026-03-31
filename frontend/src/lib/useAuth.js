"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "./users";

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const current = getCurrentUser();
    if (!current) {
      router.replace("/login");
    } else {
      setUser(current);
    }
    setLoading(false);
  }, [router]);

  return { user, loading };
}
