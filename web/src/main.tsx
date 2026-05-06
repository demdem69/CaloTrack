import React from "react";
import ReactDOM from "react-dom/client";
import "./style.css";
import { App } from "./ui/App";

const el = document.querySelector<HTMLDivElement>("#app");
if (!el) throw new Error("Missing #app");

ReactDOM.createRoot(el).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

