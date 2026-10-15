import React from "react";
import { createContext, useContext, useEffect, useState } from "react";
import { login as loginRequest } from "../api/auth";
import { authApi } from "../api/services";

const AuthContext = createContext(null);
export function AuthProvider({children}) {
  const [user,setUser]=useState(()=>JSON.parse(localStorage.getItem("edusense_user")||"null"));
  const [loading,setLoading]=useState(false);
  useEffect(()=>{const t=localStorage.getItem("edusense_token"); if(t&&!user) authApi.me().then(r=>{setUser(r.data.user);localStorage.setItem("edusense_user",JSON.stringify(r.data.user))}).catch(()=>{});},[]);
  async function login(credentials){setLoading(true);try{const r=await loginRequest(credentials);const token=r.data?.token||r.data?.access_token;const u=r.data?.user; if(!token)throw new Error("No token returned by backend.");localStorage.setItem("edusense_token",token);localStorage.setItem("edusense_user",JSON.stringify(u));setUser(u);return u}finally{setLoading(false)}}
  function logout(){localStorage.removeItem("edusense_token");localStorage.removeItem("edusense_user");setUser(null)}
  return <AuthContext.Provider value={{user,loading,login,logout}}>{children}</AuthContext.Provider>
}
export const useAuth=()=>useContext(AuthContext);