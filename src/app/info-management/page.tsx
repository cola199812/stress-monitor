import { redirect } from 'next/navigation';

export default function InfoManagementPage() {
  // 当访问 /info-management 时，默认重定向到 /info-management/entity-management
  redirect('/info-management/entity-management');
}
