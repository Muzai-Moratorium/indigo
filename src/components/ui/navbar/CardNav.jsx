import { useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { GoArrowUpRight } from "react-icons/go";
import Link from "next/link";
import "./CardNav.css";

const CardNav = ({
  logo,
  logoAlt = "Logo",
  logoText = "욜로멍",
  items,
  className = "",
  ease = "power3.out",
  baseColor = "#fff",
  menuColor,
  buttonBgColor,
  buttonTextColor,
}) => {
  const [isHamburgerOpen, setIsHamburgerOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const navRef = useRef(null);
  const cardsRef = useRef([]);
  const tlRef = useRef(null);

  const calculateHeight = () => {
    const navEl = navRef.current;
    if (!navEl) return 260;

    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (isMobile) {
      const contentEl = navEl.querySelector(".card-nav-content");
      if (contentEl) {
        const wasVisible = contentEl.style.visibility;
        const wasPointerEvents = contentEl.style.pointerEvents;
        const wasPosition = contentEl.style.position;
        const wasHeight = contentEl.style.height;

        contentEl.style.visibility = "visible";
        contentEl.style.pointerEvents = "auto";
        contentEl.style.position = "static";
        contentEl.style.height = "auto";

        contentEl.offsetHeight;

        const topBar = 60;
        const padding = 16;
        const contentHeight = contentEl.scrollHeight;

        contentEl.style.visibility = wasVisible;
        contentEl.style.pointerEvents = wasPointerEvents;
        contentEl.style.position = wasPosition;
        contentEl.style.height = wasHeight;

        return topBar + contentHeight + padding;
      }
    }
    return 260;
  };

  const createTimeline = () => {
    const navEl = navRef.current;
    if (!navEl) return null;

    gsap.set(navEl, { height: 60, overflow: "hidden" });
    gsap.set(cardsRef.current, { y: 50, opacity: 0 });

    const tl = gsap.timeline({ paused: true });

    tl.to(navEl, {
      height: calculateHeight,
      duration: 0.4,
      ease,
    });

    tl.to(
      cardsRef.current,
      { y: 0, opacity: 1, duration: 0.4, ease, stagger: 0.08 },
      "-=0.1"
    );

    return tl;
  };

  useLayoutEffect(() => {
    const tl = createTimeline();
    tlRef.current = tl;

    return () => {
      tl?.kill();
      tlRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ease, items?.length]); // items.length 추가 - 카드 개수 변경 시 타임라인 재생성

  useLayoutEffect(() => {
    const handleResize = () => {
      if (!tlRef.current) return;

      if (isExpanded) {
        const newHeight = calculateHeight();
        gsap.set(navRef.current, { height: newHeight });

        tlRef.current.kill();
        const newTl = createTimeline();
        if (newTl) {
          newTl.progress(1);
          tlRef.current = newTl;
        }
      } else {
        tlRef.current.kill();
        const newTl = createTimeline();
        if (newTl) {
          tlRef.current = newTl;
        }
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded]);

  const toggleMenu = () => {
    const tl = tlRef.current;
    if (!tl) return;
    if (!isExpanded) {
      setIsHamburgerOpen(true);
      setIsExpanded(true);
      tl.play(0);
    } else {
      setIsHamburgerOpen(false);
      tl.eventCallback("onReverseComplete", () => setIsExpanded(false));
      tl.reverse();
    }
  };

  const setCardRef = (i) => (el) => {
    if (el) cardsRef.current[i] = el;
  };

  // 메뉴 닫기 함수
  const closeMenu = () => {
    const tl = tlRef.current;
    if (tl && isExpanded) {
      setIsHamburgerOpen(false);
      tl.eventCallback("onReverseComplete", () => setIsExpanded(false));
      tl.reverse();
    }
  };

  return (
    <>
      {/* 배경 오버레이 - 클릭 시 메뉴 닫힘 */}
      {isExpanded && <div className="card-nav-overlay" onClick={closeMenu} />}
      <div className={`card-nav-container ${className}`}>
        <nav
          ref={navRef}
          className={`card-nav ${isExpanded ? "open" : ""}`}
          style={{ backgroundColor: baseColor }}
        >
          <div className="card-nav-top">
            <div
              className={`hamburger-menu ${isHamburgerOpen ? "open" : ""}`}
              onClick={toggleMenu}
              role="button"
              aria-label={isExpanded ? "Close menu" : "Open menu"}
              tabIndex={0}
              style={{ color: menuColor || "#000" }}
            >
              <div className="hamburger-line" />
              <div className="hamburger-line" />
            </div>

            <div className="logo-container">
              {logo ? (
                <img src={logo} alt={logoAlt} className="logo" />
              ) : (
                <span
                  className="logo-text"
                  style={{
                    color: menuColor || "#000",
                    fontWeight: "bold",
                    fontSize: "18px",
                  }}
                >
                  {logoText}
                </span>
              )}
            </div>

            <button
              type="button"
              className="card-nav-cta-button"
              style={{ backgroundColor: buttonBgColor, color: buttonTextColor }}
              onClick={() => (window.location.href = "/cctv")}
            >
              CCTV 시작
            </button>
          </div>

          <div className="card-nav-content" aria-hidden={!isExpanded}>
            {(items || []).slice(0, 3).map((item, idx) => (
              <div
                key={`${item.label}-${idx}`}
                className="nav-card"
                ref={setCardRef(idx)}
                style={{ backgroundColor: item.bgColor, color: item.textColor }}
              >
                <div className="nav-card-label">{item.label}</div>

                {/* customContent가 있으면 렌더링 */}
                {item.customContent && (
                  <div className="nav-card-custom">{item.customContent}</div>
                )}

                {/* 링크 목록 렌더링 */}
                <div className="nav-card-links">
                  {item.links?.map((lnk, i) =>
                    lnk.onClick ? (
                      // onClick이 있으면 버튼으로 렌더링
                      <button
                        key={`${lnk.label}-${i}`}
                        className="nav-card-link"
                        onClick={() => {
                          lnk.onClick();
                          closeMenu();
                        }}
                        aria-label={lnk.ariaLabel}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "inherit",
                          textAlign: "left",
                        }}
                      >
                        <GoArrowUpRight
                          className="nav-card-link-icon"
                          aria-hidden="true"
                        />
                        {lnk.label}
                      </button>
                    ) : lnk.href ? (
                      // href가 있으면 Next.js Link로 렌더링
                      <Link
                        key={`${lnk.label}-${i}`}
                        className="nav-card-link"
                        href={lnk.href}
                        aria-label={lnk.ariaLabel}
                        onClick={closeMenu}
                      >
                        <GoArrowUpRight
                          className="nav-card-link-icon"
                          aria-hidden="true"
                        />
                        {lnk.label}
                      </Link>
                    ) : (
                      // 기본 a 태그
                      <a
                        key={`${lnk.label}-${i}`}
                        className="nav-card-link"
                        href="#"
                        aria-label={lnk.ariaLabel}
                      >
                        <GoArrowUpRight
                          className="nav-card-link-icon"
                          aria-hidden="true"
                        />
                        {lnk.label}
                      </a>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>
        </nav>
      </div>
    </>
  );
};

export default CardNav;
