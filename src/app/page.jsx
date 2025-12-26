"use client";

import axios from "axios";
import { useState } from "react";
import "./page.module.scss";

export default function Page({ params }) {
  const { param } = params;
  const [cat, setCat] = useState(null);
  return <div className="page">page</div>;
}
