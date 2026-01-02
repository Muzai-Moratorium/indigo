"use client";

import axios from "axios";
import { useState } from "react";
import "../styles/globals.scss";
import styles from "./home.module.scss";

export default function Page({ params }) {
  const { param } = params;

  return (
    <div className={styles.home}>
      <h1>무료 Ai 홈 프로텍터</h1>
    </div>
  );
}
