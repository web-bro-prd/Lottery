import './LottoBall.css';

interface Props {
  number: number;
  bonus?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function getBallColor(num: number): string {
  if (num <= 10) return 'yellow';
  if (num <= 20) return 'blue';
  if (num <= 30) return 'red';
  if (num <= 40) return 'gray';
  return 'green';
}

export default function LottoBall({ number, bonus = false, size = 'md' }: Props) {
  const color = getBallColor(number);
  return (
    <span className={`lotto-ball ${color} ${size} ${bonus ? 'bonus' : ''}`}>
      {number}
    </span>
  );
}
