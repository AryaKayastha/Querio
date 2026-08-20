import styles from "./Avatar.module.css";

const Avatar = ({ label, size = 28, variant = "accent" }) => {
  const variantClassMap = {
    accent: "",
    dark: styles.dark,
    gold: styles.gold,
    person: styles.person,
  };

  const variantClass = variantClassMap[variant] || "";

  const dimensionStyle = {
    width: `${size}px`,
    height: `${size}px`,
    fontSize: `${Math.round(size * 0.4)}px`,
  };

  return (
    <div className={`${styles.avatar} ${variantClass}`} style={dimensionStyle}>
      {label}
    </div>
  );
};

export default Avatar;
