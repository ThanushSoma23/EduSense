import React from "react";
import { Link } from "react-router-dom";
export default function NotFound(){return <div className="screen-center"><div><h1>404</h1><p>Page not found.</p><Link className="btn btn-primary" to="/">Go home</Link></div></div>}