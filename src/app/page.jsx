"use client";

import axios from "axios";
import { useState } from "react";
import "../styles/globals.scss";
import styles from "./home.module.scss";

export default function Page({ params }) {
  const { param } = params;

  return (
    <div className={styles.home}>
      <h1>무료 Ai 생활 보호자</h1>
    </div>
  );
}
