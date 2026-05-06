export type IsoDate = string; // YYYY-MM-DD

export type Food = {
  id: string;
  name: string;
  calPer100g: number;
};

export type MealLog = {
  id: string;
  date: IsoDate;
  label: string;
  user: string;
  calories: number;
};

export type DailySpend = {
  date: IsoDate;
  user: string;
  spend: number;
};

export type GroupData = {
  groupId: string;
  passwordHashSha256: string;
  users: string[];
  foods: Food[];
  mealLogs: MealLog[];
  dailySpend: DailySpend[];
  createdAt: string;
  updatedAt: string;
  version: 1;
};

export type AppData = {
  groups: Record<string, GroupData>;
  version: 1;
};

