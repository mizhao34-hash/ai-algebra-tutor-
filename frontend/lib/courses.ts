// Course tabs in the top bar. Ids must match backend/app/courses.py; kept here
// (instead of fetched) so the navigation renders instantly, even while the
// free backend server is still waking up.
export const COURSE_TABS = [
  { id: "pre_algebra", name: "Pre-Algebra" },
  { id: "algebra_1", name: "Algebra 1" },
  { id: "algebra_2", name: "Algebra 2" },
] as const;
