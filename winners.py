import numpy as np
from scipy.stats import norm

class DGP(object):
    
    def __init__(self, nsamples, narms, means, vars):
        self.n = nsamples
        self.k = narms
        self.means = means
        self.vars = vars
        if self.verify_inputs() is False:
            raise ValueError("Incorrect inputs.")
        
    def verify_inputs(self):
        if len(self.means) != self.k or len(self.vars) != self.k:
            return False
        if self.n % self.k != 0:
            return False
        return True
    
    def get_potentials(self):
        Y = np.zeros((self.n, self.k))
        for i in range(self.k):
            Y[:,i] = np.random.normal(self.means[i], self.vars[i], size=self.n)
        return Y
    
    def get_treatment(self):
        Z = []
        for i in range(self.k):
            Z += [i]*int(self.n/self.k)
        Z = np.array(Z)
        np.random.shuffle(Z)
        return Z
    
    def get_data(self):
        Yp = self.get_potentials()
        Z = self.get_treatment()
        Y = np.zeros(self.n)
        for i in range(self.k):
            Y[Z==i] = Yp[Z==i,i]
        return Y, Z
    
    
class RD(object):
    
    def __init__(self, Y, Z, b, null=0):
        self.n = len(Y)
        self.Y = Y
        self.Z = Z
        self.b = b
        self.narms = len(set(Z))
        self.null = null
        if set(Z) != set(np.arange(self.narms)):
            raise ValueError("Wrong Z.")
        
    def sample_splitting(self, Y, Z, row_idx1):
        idx = np.arange(self.n)
        #row_idx1 = np.random.choice(idx, self.b, replace=False)
        row_idx2 = np.array(list(set(idx) - set(row_idx1)))
        Y1, Z1, Y2, Z2 = Y[row_idx1], Z[row_idx1], Y[row_idx2], Z[row_idx2]
        best_arm = self.get_best_arm(Y1, Z1)
        mean_best = np.mean(Y2[Z2==best_arm])
        var_best = np.var(Y2[Z2==best_arm])
        se = np.sqrt(var_best/len(Y2[Z2==best_arm]))
        t = mean_best/se
        cf = (mean_best-norm.ppf(0.975)*se, mean_best+norm.ppf(0.975)*se)
        pval = (1-norm.cdf(np.abs(t)))*2
        return mean_best, se, t, cf, pval
        
    def get_best_arm(self, Y, Z):
        arms = list(set(Z))
        best_arm = arms[0]
        best_mean = -np.inf
        for i in arms:
            mean = np.mean(Y[Z==i])
            if mean > best_mean:
                best_arm = i
                best_mean = mean
        return best_arm
    
    def get_residual(self):
        mu_params = np.zeros(self.narms)
        for i in range(self.narms):
            mu_params[i] = np.mean(self.Y[self.Z==i])
            #mu_params[i] = (np.arange(5)-4)[i]
        mu_params[np.argmax(mu_params)] = self.null
        mu = mu_params[self.Z]
        return self.Y-mu, mu_params
    
    def single_test(self):
        idx = np.arange(self.n)
        row_idx1 = np.random.choice(idx, self.b, replace=False)
        return self.sample_splitting(self.Y, self.Z, row_idx1)[-1]
    
    def multiple_test(self, ntests, ntrans):
        idx = np.arange(self.n)
        row_idx1s = [np.random.choice(idx, self.b, replace=False) for i in range(ntests)]
        pvals = np.zeros(ntrans)
        eps, mu = self.get_residual()
        # get p_obs
        p_obs = np.mean([self.sample_splitting(self.Y, self.Z, ridx)[-1] for ridx in row_idx1s])
        for i in range(ntrans):
            # permute Z
            Z = self.Z.copy()
            np.random.shuffle(Z)
            # residual randomization
            g = np.random.choice([0,1],size=len(Z))
            Y = mu[Z] + g*eps
            ps = [self.sample_splitting(Y, Z, ridx)[-1] for ridx in row_idx1s]
            p = np.mean(ps)
            pvals[i] = p
        pvalue = np.mean(pvals < p_obs)
        return pvalue


