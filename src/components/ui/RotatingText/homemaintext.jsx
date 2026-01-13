import React from "react";
import RotatingText from "./RotatingText";
import styles from "./homemaintext.module.scss";

function homemaintext() {
  return (
    <div className={styles.wrapper}>
      <RotatingText
        className={styles.textRotate}
        texts={["가족", "집", "나"]}
        mainClassName="px-2 sm:px-2 md:px-3 bg-cyan-300 text-black overflow-hidden py-0.5 sm:py-1 md:py-2 justify-center rounded-lg"
        staggerFrom={"last"}
        initial={{ y: "80%" }}
        animate={{ y: "0%" }}
        exit={{ y: "-10%" }}
        staggerDuration={0.005}
        splitLevelClassName="overflow-hidden pb-0.5 sm:pb-1 md:pb-1"
        transition={{ type: "spring", damping: 80, stiffness: 500 }}
        rotationInterval={3000}
      />
    </div>
  );
}

export default homemaintext;
