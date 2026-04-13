'use client';

import * as z from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { LoginRequest } from '@/lib/service/account';
import { authService } from '@/lib/service/account/api';

const loginSchema = z.object({
    username: z.string().min(3, { message: 'Username ít nhất 3 ký tự' }),
    password: z.string().min(6, { message: 'Password bèo nhất 6 ký tự' }),
});

export default function LoginPage() {
    const router = useRouter();
    const setToken = useAuthStore((state) => state.setToken);
    const setUser = useAuthStore((state) => state.setUser);

    const form = useForm<z.infer<typeof loginSchema>>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            username: '',
            password: '',
        },
    });

    const loginMutation = useMutation({
        mutationFn: (values: LoginRequest) => authService.login(values),
        onSuccess: async (data) => {
            setToken(data.access_token);
            
            try {
                const userProfile = await authService.getMe();
                setUser({
                    id: userProfile.id,
                    email: '',
                    name: userProfile.username,
                    provider: 'local',
                    createAt: new Date().toISOString(),
                    role: userProfile.role,
                    permissions: [],
                    active: true,
                });
                
                router.push('/knowledge-base');
            } catch (error) {
                console.error('Lỗi khi fetch profile:', error);
            }
        },
        onError: (error) => {
            console.error('Login failed:', error);
        },
    });

    const onSubmit = (values: z.infer<typeof loginSchema>) => {
        loginMutation.mutate(values);
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-black text-zinc-50">
            <div className="w-full max-w-md p-8 bg-zinc-950 border border-zinc-800 rounded-sm shadow-xl">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-bold mb-2">SEAL Copilot</h1>
                    <p className="text-zinc-400">Đăng nhập hệ thống nội bộ</p>
                </div>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                        <FormField
                            control={form.control}
                            name="username"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="text-zinc-300">Username</FormLabel>
                                    <FormControl>
                                        <Input 
                                            placeholder="ops_namdang" 
                                            className="bg-zinc-900 border-zinc-800 text-white focus-visible:ring-zinc-700" 
                                            {...field} 
                                        />
                                    </FormControl>
                                    <FormMessage className="text-red-400" />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="text-zinc-300">Password</FormLabel>
                                    <FormControl>
                                        <Input 
                                            type="password" 
                                            placeholder="••••••••" 
                                            className="bg-zinc-900 border-zinc-800 text-white focus-visible:ring-zinc-700" 
                                            {...field} 
                                        />
                                    </FormControl>
                                    <FormMessage className="text-red-400" />
                                </FormItem>
                            )}
                        />

                        <Button 
                            type="submit" 
                            className="w-full bg-white text-black hover:bg-zinc-200 transition font-medium"
                            disabled={loginMutation.isPending}
                        >
                            {loginMutation.isPending ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Đang xác thực...
                                </>
                            ) : (
                                'Đăng nhập'
                            )}
                        </Button>
                    </form>
                </Form>
            </div>
        </div>
    );
}
